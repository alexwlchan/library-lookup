function getAvailabilityMessage(availability) {
  if (availability.locallyAvailableCopies === 1) {
    return '1 copy nearby';
  } else if (availability.locallyAvailableCopies > 0) {
    return `${availability.locallyAvailableCopies} copies nearby`;
  }

  if (availability.availableCopies === 0) {
    return 'No copies';
  } else if (availability.availableCopies === 1 && availability.locallyAvailableCopies === 0) {
    return `${availability.availableCopies} copy`;
  } else if (availability.locallyAvailableCopies === 0) {
    return `${availability.availableCopies} copies`;
  } else if (availability.availableCopies === 1 && availability.locallyAvailableCopies === 1) {
    return '1 copy, nearby';
  } else {
    return `${availability.availableCopies} copies, ${availability.locallyAvailableCopies} nearby`;
  };
}

function getAvailabilityDescription(availability) {
    const callNumber = availability.call_number.replaceAll(" pbk", " paperback");

    if (availability.collection === 'Fiction' && callNumber.startsWith('General fiction')) {
        return `${availability.location} / ${callNumber}`;
    }

    if (availability.collection === 'Fiction' && callNumber.startsWith('Science fiction')) {
        return `${availability.location} / ${callNumber}`;
    }

    return callNumber !== ""
        ? `${availability.location} / ${availability.collection} / ${callNumber}`
        : `${availability.location} / ${availability.collection}`
}

function getListOfCopies(availability) {
  const talliedAvailability = availability
    .map(av => getAvailabilityDescription(av))
    .reduce((tally, av) => {
        tally[av] = (tally[av] || 0) + 1;
        return tally;
    }, {});

  const labels = Object.entries(talliedAvailability)
    .map(entry => {
      const [label, count] = entry;
      return count > 1 ? `${label} (&times;&thinsp;${count})` : label;
    });

  return '<ul>' + labels.map(lab => `<li>${lab}</li>`).join('') + '</ul>';
}

/* https://stackoverflow.com/q/1960473/1558022 */
function onlyUnique(value, index, array) {
  return array.indexOf(value) === index;
}

function getAvailabilityInfo(availability) {
  const extraLocations =
    availability.availableLocations
      .filter(av => availability.locallyAvailableLocations.indexOf(av) === -1)
      .map(av => av.location)
      .map(location =>
        location.endsWith(' Community Library')
          ? location
          : location.endsWith(' Library')
          ? location.replace(/ Library$/, '')
          : location
      )
      .map(location => `<span class="location_name">${location}</span>`)
      .filter(onlyUnique);

  extraLocations.sort();

  const extraLocationMessage =
    extraLocations.length === 1
      ? extraLocations[0]
      : extraLocations.length == 2
      ? `${extraLocations[0]} and ${extraLocations[1]}`
      : `${extraLocations.slice(0, extraLocations.length - 1).join(", ")} and ${extraLocations[extraLocations.length - 1]}`;

  if (availability.locallyAvailableCopies === 0) {
    switch(availability.availableCopies) {
      case 0:
        return '<p>No copies available.</p>';
      case 1:
        return `<p>1 copy available in ${extraLocationMessage}.</p>`;
      default:
        return `<p>${availability.availableCopies} copies available in ${extraLocationMessage}.</p>`;
    }
  }

  const availabilityMessage =
    availability.locallyAvailableCopies === 1
      ? '<p><strong>1 copy available nearby.</strong></p>' + getListOfCopies(availability.locallyAvailableLocations)
      : `<p><strong>${availability.locallyAvailableCopies} copies available nearby.</strong></p>` + getListOfCopies(availability.locallyAvailableLocations);

  switch (availability.availableCopies) {
    case 0:
      return availabilityMessage;
    case 1:
      return `${availabilityMessage}<p class="extra_copies">plus 1 more copy in ${extraLocationMessage}.</p>`
    default:
      return `${availabilityMessage}<p class="extra_copies">plus ${availability.availableCopies} more copies in ${extraLocationMessage}.</p>`
  }
}

function renderBooks() {
  const selectedBranches =
    Array.from(document.querySelectorAll('#branch_picker input'))
      .filter(input => input.checked)
      .map(input => input.value);

  // Store the list of selected branches in localStorage
  window.localStorage.setItem("branchesSelected", JSON.stringify(selectedBranches));

  // Build a tally { bookId => how many available copies }
  const bookAvailability = Object.fromEntries(
    books
      .map(function(book) {
        const availableLocations = book.availability
          .filter(av => av.status === 'Available');

        const locallyAvailableLocations = availableLocations
          .filter(av => selectedBranches.includes(av.location));

        const locallyAvailableCopies = locallyAvailableLocations.length;

        const availableCopies = availableLocations
          .filter(av => !selectedBranches.includes(av.location))
          .length;

        return [book.record_details.BRN, { locallyAvailableCopies, locallyAvailableLocations, availableLocations, availableCopies } ];
      })
  );

  // Go through each book, and work out how many of its copies are
  // available.  Store these in a list [<book>, count]
  let updatedBooks = [];
  for (book of document.querySelectorAll('#books .book')) {
    const availability = bookAvailability[book.getAttribute('data-book-brn')];

    if (availability.locallyAvailableCopies === 0) {
      book.classList.add("no_local_copies");
    } else {
      book.classList.remove("no_local_copies");
    }

    const title = book.getAttribute('data-book-title');
    const year = book.getAttribute('data-book-year');

    book.querySelector('.availability').innerHTML = getAvailabilityInfo(availability);

    for (tr of book.querySelectorAll('.availability tr')) {
      if (availability.locallyAvailableLocations.includes(tr.getAttribute('data-av-location')) && tr.getAttribute('data-av-status') === 'Available') {
        tr.classList.remove('unavailable');
      } else {
        tr.classList.add('unavailable');
      }
    }

    updatedBooks.push({ book, title, year, locallyAvailableCopies: availability.locallyAvailableCopies });
  }

  // Sort the books so those with the most copies are at the top.
  // If two books have the same number of copies, arbitrarily sort
  // by title.
  updatedBooks.sort(function(a, b) {
    if (a.locallyAvailableCopies === b.locallyAvailableCopies && a.title === b.title) {
      return Number(b.year) - Number(a.year)
    } else if (a.locallyAvailableCopies === b.locallyAvailableCopies) {
      return a.title > b.title ? 1 : -1;
    } else {
      return b.locallyAvailableCopies - a.locallyAvailableCopies;
    }
  });

  let elements = document.createDocumentFragment();
  for (book of updatedBooks) {
    elements.appendChild(book.book.cloneNode(true));
  }

  document.querySelector('#books').innerHTML = null;
  document.querySelector('#books').appendChild(elements);

  if (selectedBranches.length > 0) {
document.querySelector('#selectedBranchCount').innerHTML = `(${selectedBranches.length} selected – ${selectedBranches.join("; ")})`
  } else {
    document.querySelector('#selectedBranchCount').innerHTML = '';
  }
}

// Renders a date in the local timezone, including day of the week.
// e.g. "Fri, 22 May 2020"
const dateFormatter = new Intl.DateTimeFormat(
  [], {"year": "numeric", "month": "long", "day": "numeric", "weekday": "short"}
)

// Renders an HH:MM time in the local timezone, including timezone info.
// e.g. "12:17 BST"
const timeFormatter = new Intl.DateTimeFormat(
  [], {"hour": "numeric", "minute": "numeric"}
)

// Given an ISO 8601 date string, render it as a more friendly date
// in the user's timezone.
//
// Examples:
// - "today @ 12:00 BST"
// - "yesterday @ 11:00 CST"
// - "Fri, 22 May 2020 @ 10:00 PST"
//
// From https://alexwlchan.net/2020/human-friendly-dates-in-javascript/
//
function getHumanFriendlyDateString(iso8601_date_string) {
  const date = new Date(Date.parse(iso8601_date_string));

  // When are today and yesterday?
  const today = new Date();
  const yesterday = new Date().setDate(today.getDate() - 1);

  // We have to compare the *formatted* dates rather than the actual dates --
  // for example, if the UTC date and the localised date fall on either side
  // of midnight.
  if (dateFormatter.format(date) == dateFormatter.format(today)) {
    return "today at " + timeFormatter.format(date);
  } else if (dateFormatter.format(date) == dateFormatter.format(yesterday)) {
    return "yesterday at " + timeFormatter.format(date);
  } else {
    return dateFormatter.format(date) + " at " + timeFormatter.format(date);
  }
}
